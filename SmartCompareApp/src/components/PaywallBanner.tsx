/**
 * Paywall takeover banner — replaces TwoInputShell when `canCompare === false`.
 *
 * Spec: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 6.2
 *
 * Build Principle #4 — copy reframes "out of comparisons" as "you've used
 * your free ones" + "unlock". No error or scary vocabulary.
 */
import React from 'react';
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { Lock } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import {
  arabicLineHeightMultiplier,
  colors,
  radii,
  shadows,
  spacing,
  typography,
} from '../theme';

export interface PaywallBannerProps {
  onSeeOptions: () => void;
  testID?: string;
}

function PaywallBanner({ onSeeOptions, testID = 'paywall-banner' }: PaywallBannerProps) {
  const { t, i18n } = useTranslation();
  const isAR = i18n.language?.startsWith('ar');

  const handlePress = () => {
    try {
      const maybePromise = Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      if (maybePromise && typeof maybePromise.catch === 'function') {
        maybePromise.catch(() => {});
      }
    } catch {
      /* haptic engine unavailable — proceed */
    }
    onSeeOptions();
  };

  const arLineHeight = (base: number) => base * arabicLineHeightMultiplier;

  return (
    <View style={styles.outer}>
      <View style={styles.card} testID={testID}>
        <View style={styles.iconCircle}>
          <Lock size={24} color={colors.accent} />
        </View>
        <Text
          style={[
            styles.title,
            isAR && { lineHeight: arLineHeight(typography.display.lineHeight) },
          ]}
        >
          {t('home.compare.paywall_banner_title')}
        </Text>
        <Text
          style={[
            styles.body,
            isAR && { lineHeight: arLineHeight(typography.body.lineHeight) },
          ]}
        >
          {t('home.compare.paywall_banner_body')}
        </Text>
        <TouchableOpacity
          testID={`${testID}-cta`}
          style={styles.cta}
          onPress={handlePress}
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>
            {t('home.compare.paywall_banner_cta')}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const ICON_CIRCLE = 40;

const styles = StyleSheet.create({
  outer: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  card: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing['2xl'],
    alignItems: 'center',
    ...shadows.card,
  },
  iconCircle: {
    width: ICON_CIRCLE,
    height: ICON_CIRCLE,
    borderRadius: ICON_CIRCLE / 2,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  body: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 320,
    marginBottom: spacing.xl,
  },
  cta: {
    width: '100%',
    height: 48,
    borderRadius: radii.button,
    backgroundColor: colors.cta.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: {
    ...typography.bodyEmphasis,
    color: colors.cta.onPrimary,
  },
});

export default PaywallBanner;

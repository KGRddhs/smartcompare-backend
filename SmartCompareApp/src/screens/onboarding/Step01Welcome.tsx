/**
 * Step01Welcome — Bundle E S2.W1 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingWelcomeScreen.jsx
 * (full file, lines 14-93). REWRITTEN top-down per the JSX — the prior
 * Phase 2 anatomy (96px black Q-badge centered hero + title + subtitle
 * + Continue) was structurally different from the JSX (warm-wash bg +
 * 40px QarenLogo top-left + headline + QuoteRow trio + Continue +
 * sign-in link).
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — the visual anchor moves from a giant centered logo
 * badge to a smaller top-anchored brand mark + 3 testimonial cards as
 * the credibility hook above the CTA. The two layouts share only the
 * Continue button + sign-in link affordance.
 *
 * New anatomy (top-down per JSX):
 *   1. Warm-wash background — two absolutely-positioned tinted corner
 *      Views approximating the JSX dual-radial-gradient (orange upper-
 *      right + cool blue upper-left). Per dispatcher ruling (Q), NOT
 *      installing expo-linear-gradient — RN's linear-only gradient
 *      can't render the JSX radial recipe anyway. Upgrade to
 *      expo-linear-gradient when the next EAS rebuild lands per
 *      task #34.
 *   2. QarenLogo size=40 (replacing the 96px black square badge). The
 *      JSX uses a much smaller, less-anchored brand mark to make room
 *      for the QuoteRow trio.
 *   3. Headline ("Look closer. Decide smarter.") + subtitle ("Built
 *      for the GCC. By people like you."). Copy unchanged.
 *   4. QuoteRow trio — 3 testimonial cards verbatim from JSX:46-48:
 *        - "Picked Galaxy — camera + battery edged out Apple here"
 *        - "Picked La Roche — matched my sensitive-skin tag"
 *        - "Picked Centrum — better nutrient profile"
 *      Sources brand cred BEFORE the user commits to onboarding. Lift
 *      via i18n keys so AR can localize.
 *   5. Continue button + "Already have an account? Sign in" link
 *      (unchanged).
 *
 * Test contract preserved (Step01Welcome.test.tsx — 5 tests):
 *   - testID="welcome-qicon" still on the brand-mark wrapper (now
 *     wrapping QarenLogo instead of the 96px badge)
 *   - testID="welcome-continue" on the Continue Button
 *   - testID="welcome-sign-in-link" on the sign-in TouchableOpacity
 *   - onboarding.s1.{title,continue,sign_in_link} still render
 *   - sign-in link omitted when onSignIn prop is absent
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import QarenLogo from '../../components/QarenLogo';
import { QuoteRow } from '../../components/primitives/QuoteRow';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
  onSignIn?: () => void;
}

export function Step01Welcome({ onNext, onSignIn }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      {/* Warm-wash bg — two absolutely-positioned tinted corners.
          RN approximation of the JSX dual-radial-gradient per
          dispatcher ruling Q. Upgrade tracked as task #34. */}
      <View pointerEvents="none" style={styles.warmCornerLeft} testID="welcome-warm-left" />
      <View pointerEvents="none" style={styles.warmCornerRight} testID="welcome-warm-right" />

      {/* Brand mark — small + top-anchored per JSX (replaces 96px badge).
          testID stays "welcome-qicon" for back-compat with existing
          Step01Welcome tests. */}
      <View style={styles.brandRow} testID="welcome-qicon">
        <QarenLogo size={40} />
      </View>

      <View style={styles.headlineBlock}>
        <Text style={styles.title}>{t('onboarding.s1.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s1.subtitle')}</Text>
      </View>

      <View style={styles.quoteStack}>
        <QuoteRow
          testID="welcome-quote-1"
          quote={t('onboarding.s1.quote_1', {
            defaultValue:
              'Picked Galaxy — camera + battery edged out Apple here.',
          })}
        />
        <QuoteRow
          testID="welcome-quote-2"
          quote={t('onboarding.s1.quote_2', {
            defaultValue: 'Picked La Roche — matched my sensitive-skin tag.',
          })}
        />
        <QuoteRow
          testID="welcome-quote-3"
          quote={t('onboarding.s1.quote_3', {
            defaultValue: 'Picked Centrum — better nutrient profile.',
          })}
        />
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s1.continue')}
          variant="primary"
          onPress={onNext}
          testID="welcome-continue"
        />
        {onSignIn ? (
          <TouchableOpacity
            onPress={onSignIn}
            accessibilityRole="link"
            style={styles.signInWrap}
            testID="welcome-sign-in-link"
          >
            <Text style={styles.signInText}>
              {t('onboarding.s1.sign_in_link')}
            </Text>
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

// Warm-wash corner tint sizing — JSX uses 120% × 60% radial reach
// per corner. 360×260 absolute boxes with low-alpha fills approximate
// the visual wash without the radial falloff (RN limitation).
const WARM_W = 360;
const WARM_H = 260;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
    paddingBottom: spacing.lg,
    backgroundColor: colors.bg.primary,
  },
  // Cool blue tint — upper-LEFT corner per JSX gradient #2.
  warmCornerLeft: {
    position: 'absolute',
    top: -WARM_H * 0.5,
    left: -WARM_W * 0.3,
    width: WARM_W,
    height: WARM_H,
    backgroundColor: 'rgba(190,200,255,0.22)',
    borderRadius: WARM_W,
  },
  // Warm orange tint — upper-RIGHT corner per JSX gradient #1.
  warmCornerRight: {
    position: 'absolute',
    top: -WARM_H * 0.5,
    right: -WARM_W * 0.3,
    width: WARM_W,
    height: WARM_H,
    backgroundColor: 'rgba(255,200,160,0.22)',
    borderRadius: WARM_W,
  },
  brandRow: {
    paddingTop: spacing.sm,
    paddingBottom: spacing['2xl'],
  },
  headlineBlock: {
    marginBottom: spacing.xl,
  },
  title: {
    // Match JSX h1: 700 38/1.1 letterSpacing -0.5 textWrap pretty.
    // typography.hero is 36/1.2 700 letterSpacing 36×-0.02 (~-0.72).
    // Use hero as base then bump fontSize to 38 + tighten line-height
    // to 1.1 to match the JSX exactly.
    fontSize: 38,
    fontWeight: '700',
    lineHeight: 38 * 1.1,
    letterSpacing: -0.5,
    color: colors.text.primary,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    marginTop: spacing.md,
    maxWidth: 320,
  },
  quoteStack: {
    gap: spacing.sm,
    marginBottom: spacing.xl,
  },
  footer: {
    marginTop: 'auto',
    paddingTop: spacing.md,
  },
  signInWrap: {
    marginTop: spacing.sm,
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  signInText: {
    ...typography.body,
    color: colors.text.secondary,
  },
});

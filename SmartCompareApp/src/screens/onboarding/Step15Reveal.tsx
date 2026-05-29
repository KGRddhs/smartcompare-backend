/**
 * Step15Reveal — Bundle E S2.W4 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingReadyScreen.jsx
 * (full file, lines 14-110). The pay-off moment at the end of onboarding.
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — the prior Phase 2 anatomy (RevealBurst hero + ad-hoc
 * StatCard cells + CounterTicker peerCount) is replaced with the JSX-spec
 * MatchBadge primitive + 4× StatBlock 2x2 grid. RevealBurst is dropped
 * here per QA § 6 audit (it stays exclusive to ResultsScreen now).
 *
 * New anatomy (top-down per JSX):
 *   1. MatchBadge primitive — 88px emerald-accentLight circle + "92%" +
 *      ✦ sparkle accent + "Strong match" eyebrow.
 *   2. Headline "Your shopping advisor is ready." + subtitle
 *      "Tuned to your priorities. Trained by your peers."
 *   3. 4× StatBlock 2x2 grid:
 *        a. Top priority (e.g. "Quality") — accent=true (emerald value)
 *        b. Budget tier (e.g. "Mid-range")
 *        c. Peers in {governorate} (e.g. "2,000+")
 *        d. GCC cohort (e.g. "15,000+")
 *   4. CTA "Compare your first product".
 *
 * The 80ms staggered Animated.View wrap stays — the StatBlock primitive
 * itself is layout-stable; the wrapper carries the reveal choreography.
 *
 * Profile shape:
 *   - The OnboardingFlow passes the accumulated demographic data
 *     (priorities, budget, brand_attitude, country, governorate, …) as
 *     `profile`. Step15 derives the 4 display values + match percent
 *     itself so callers don't need to compute them. Display lookups
 *     route through t() so EN / AR copy stays localized.
 *
 * Governorate substitution:
 *   - "Peers in {governorate}" label substitutes the localized
 *     governorate label per qaren-cohort privacy invariant — null /
 *     undefined falls back to "Peers in the GCC" via the same
 *     gcc_fallback discipline as Step13 + Step14.
 */

import React, { useEffect, useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withDelay,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { MatchBadge } from '../../components/primitives/MatchBadge';
import { StatBlock } from '../../components/primitives/StatBlock';
import { colors, spacing, typography } from '../../theme';
import {
  OnboardingBudget,
  OnboardingBrandAttitude,
  OnboardingCountry,
  OnboardingGovernorate,
} from './types';

export interface RevealProfile {
  /** Numeric match percent for MatchBadge (default 92 per JSX). */
  matchQuality?: number;
  /** 1-3 of 8 canonical priority keys; first is the display "Top priority". */
  priorities?: string[];
  /** 5-tier enum from Step09. */
  budget?: OnboardingBudget;
  brand_attitude?: OnboardingBrandAttitude;
  age_group?: string;
  gender?: string;
  country?: OnboardingCountry;
  governorate?: OnboardingGovernorate;
}

interface Props {
  onNext: () => void;
  profile: RevealProfile;
}

const STAGGER_MS = 80;
const SLIDE_PX = 24;
const FADE_MS = 320;
// Stats begin entering AFTER the MatchBadge mount + headline settle
// (~600ms) so the reveal sequence reads as theatrical rather than
// simultaneous overlay.
const CARDS_START_DELAY_MS = 600;
const DEFAULT_MATCH_PCT = 92;
// Per JSX OnboardingReadyScreen.jsx:91-92 — the GCC and per-governorate
// peer counts are display-only nominal figures. Real cohort population
// is surfaced by the backend on first comparison, not at onboarding-
// ready time. Keep these stable so the moment feels confident.
const PEERS_GOVERNORATE_DISPLAY = '2,000+';
const PEERS_GCC_DISPLAY = '15,000+';

function StaggeredCardWrap({
  children,
  delayMs,
  testID,
}: {
  children: React.ReactNode;
  delayMs: number;
  testID: string;
}) {
  const opacity = useSharedValue(0);
  const translateY = useSharedValue(SLIDE_PX);

  useEffect(() => {
    opacity.value = withDelay(
      delayMs,
      withTiming(1, { duration: FADE_MS, easing: Easing.out(Easing.cubic) }),
    );
    translateY.value = withDelay(
      delayMs,
      withTiming(0, { duration: FADE_MS, easing: Easing.out(Easing.cubic) }),
    );
  }, [opacity, translateY, delayMs]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateY: translateY.value }],
  }));

  return (
    <Animated.View
      testID={testID}
      style={[styles.cardWrap, animatedStyle]}
    >
      {children}
    </Animated.View>
  );
}

export function Step15Reveal({ onNext, profile }: Props) {
  const { t } = useTranslation();

  // Derived display values — Step15 owns the priority + budget i18n
  // lookups so OnboardingFlow keeps passing raw demographic data.
  const matchPercent = profile.matchQuality ?? DEFAULT_MATCH_PCT;

  const topPriorityDisplay = useMemo(() => {
    const first = profile.priorities?.[0];
    if (!first) return t('onboarding.s15.empty_priority', { defaultValue: '—' });
    return t(`onboarding.s8.priority_${first}`, { defaultValue: first });
  }, [profile.priorities, t]);

  const budgetDisplay = useMemo(() => {
    if (!profile.budget) {
      return t('onboarding.s15.empty_budget', { defaultValue: '—' });
    }
    return t(`onboarding.s9.${profile.budget}`, { defaultValue: profile.budget });
  }, [profile.budget, t]);

  const governorateDisplay = useMemo(() => {
    if (!profile.governorate) {
      return t('onboarding.s13.gcc_fallback', { defaultValue: 'the GCC' });
    }
    return t(`onboarding.s4.gov_${profile.governorate.toLowerCase()}`, {
      defaultValue: profile.governorate,
    });
  }, [profile.governorate, t]);

  const peersLabel = t('onboarding.s15.peers_in', {
    governorate: governorateDisplay,
    defaultValue: `Peers in ${governorateDisplay}`,
  });

  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <MatchBadge
          percent={matchPercent}
          eyebrow={t('onboarding.s15.match_strong', { defaultValue: 'Strong match' })}
          testID="s15-match-badge"
        />
        <Text style={styles.title} testID="s15-title">
          {t('onboarding.s15.title')}
        </Text>
        <Text style={styles.subtitle} testID="s15-subtitle">
          {t('onboarding.s15.subtitle', {
            defaultValue: 'Tuned to your priorities. Trained by your peers.',
          })}
        </Text>
      </View>

      <View style={styles.grid}>
        <View style={styles.gridRow}>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 0}
            testID="stat-card-wrap-0"
          >
            <StatBlock
              testID="stat-top-priority"
              label={t('onboarding.s15.top_priority', { defaultValue: 'Top priority' })}
              value={topPriorityDisplay}
              accent
            />
          </StaggeredCardWrap>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 1}
            testID="stat-card-wrap-1"
          >
            <StatBlock
              testID="stat-budget-tier"
              label={t('onboarding.s15.budget_tier', { defaultValue: 'Budget tier' })}
              value={budgetDisplay}
            />
          </StaggeredCardWrap>
        </View>
        <View style={styles.gridRow}>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 2}
            testID="stat-card-wrap-2"
          >
            <StatBlock
              testID="stat-peers-in"
              label={peersLabel}
              value={PEERS_GOVERNORATE_DISPLAY}
            />
          </StaggeredCardWrap>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 3}
            testID="stat-card-wrap-3"
          >
            <StatBlock
              testID="stat-gcc-cohort"
              label={t('onboarding.s15.gcc_cohort', { defaultValue: 'GCC cohort' })}
              value={PEERS_GCC_DISPLAY}
            />
          </StaggeredCardWrap>
        </View>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s15.cta', {
            defaultValue: 'Compare your first product',
          })}
          variant="primary"
          onPress={onNext}
          testID="s15-cta"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    justifyContent: 'space-between',
  },
  hero: {
    alignItems: 'center',
    paddingTop: spacing.lg,
    gap: spacing.md,
  },
  // JSX h1: 700 28/1.2 letterSpacing -0.32 textAlign center max-width 320.
  title: {
    fontSize: 28,
    fontWeight: '700',
    lineHeight: 28 * 1.2,
    letterSpacing: -0.32,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  // JSX subtitle: 400 14/1.5 secondary maxWidth 320.
  subtitle: {
    ...typography.body,
    fontSize: 14,
    lineHeight: 14 * 1.5,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 320,
  },
  grid: {
    gap: spacing.md,
    marginVertical: spacing.lg,
  },
  gridRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  cardWrap: {
    flex: 1,
  },
  footer: {
    paddingTop: spacing.lg,
  },
});

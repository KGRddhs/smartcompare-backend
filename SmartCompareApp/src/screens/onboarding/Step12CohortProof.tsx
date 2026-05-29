/**
 * Step12CohortProof — Phase 2 Task 19 + Phase 5 polish.
 *
 * "388 GCC shoppers helped train this." Hero illustration #2 + 3 bullet
 * stats. Sunk-cost + trust + "I'm not alone." First moment in the flow
 * where the cohort moat earns its visibility per design § 6.
 *
 * Phase 5 polish: 3 bullets stagger-fade-in 80ms each per design § 1
 * "Card slide-in: Stagger 80ms, slide 24px from below + fade". Same
 * choreography pattern reused on Step 15 reveal stat cards.
 */

import React, { useEffect } from 'react';
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
import { PeerLattice } from '../../components/hero/PeerLattice';
import { CohortBullet } from '../../components/primitives/CohortBullet';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
  totalShoppers?: number;
  userCohortSize?: number;
}

const STAGGER_MS = 80;
const SLIDE_PX = 24;
const FADE_MS = 320;
// Bullets begin entering AFTER the chart's bar/dot intro (~1.0s) so they
// land as a sequenced reveal rather than a simultaneous overlay.
const BULLET_START_DELAY_MS = 1000;

// F-S2.W1: Inner content swapped from <Animated.Text> to the S0.3
// <CohortBullet> primitive (emerald-tint 24px circle + check glyph +
// bullet text per JSX OnboardingCohortScreen.jsx:22-39). The stagger
// fade+slide animation now wraps CohortBullet in an <Animated.View>
// per prep doc § Step12 — same choreography contract, primitive owns
// the visual recipe.
//
// F-S2.W1.hotfix (task #35): On device the bullets rendered invisible
// because the outer Animated.View had no width style + the parent
// bullets container uses alignItems:'center'. With alignItems:center
// children that don't set width OR alignSelf:'stretch' collapse to
// their content's intrinsic size, but CohortBullet's row uses
// `flex: 1` on the text label which distributes 0 extra space when
// the row itself has no width constraint — net result: row collapses
// horizontally and the text becomes 0-width / invisible. Fix: stretch
// the Animated.View to its parent's width via `alignSelf: 'stretch'`
// so the inner row has room to lay out the text label. Jest didn't
// catch this because RN's test renderer doesn't enforce layout
// constraints (text always reports its full string), only the device
// runtime collapses the row.
function StaggeredBullet({
  text,
  delayMs,
  testID,
}: {
  text: string;
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
      style={[styles.bulletStretch, animatedStyle]}
      testID={testID}
    >
      <CohortBullet icon="check" text={text} />
    </Animated.View>
  );
}

export function Step12CohortProof({
  onNext,
  // totalShoppers + userCohortSize are kept in Props for backward compat
  // (callers pass them today) but the JSX-spec PeerLattice hero is
  // self-contained (cohort position derived from its 12×7 lattice + center
  // YOU-dot), so they are unused here. S2 will rewire Step12 fully to
  // consume them via PeerLattice props once that API extends.
  totalShoppers: _totalShoppers,
  userCohortSize: _userCohortSize,
}: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <PeerLattice testID="s12-bar-chart" />

        <Text style={styles.title}>{t('onboarding.s12.title')}</Text>

        <View style={styles.bullets}>
          <StaggeredBullet
            text={t('onboarding.s12.bullet_1')}
            delayMs={BULLET_START_DELAY_MS}
            testID="s12-bullet-0"
          />
          <StaggeredBullet
            text={t('onboarding.s12.bullet_2')}
            delayMs={BULLET_START_DELAY_MS + STAGGER_MS}
            testID="s12-bullet-1"
          />
          <StaggeredBullet
            text={t('onboarding.s12.bullet_3')}
            delayMs={BULLET_START_DELAY_MS + STAGGER_MS * 2}
            testID="s12-bullet-2"
          />
        </View>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s12.continue')}
          variant="primary"
          onPress={onNext}
          testID="s12-continue"
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
  heroBlock: {
    flex: 1,
    alignItems: 'center',
    paddingTop: spacing.lg,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  // F-S2.W1: CohortBullet primitive owns the per-row layout (24px circle
  // + 15/500 left-aligned text), so the outer container only sets the
  // vertical gap + horizontal padding. Removed the bullet text style
  // and the alignItems:'center' centering (CohortBullet left-aligns by
  // design per JSX OnboardingCohortScreen.jsx).
  //
  // F-S2.W1.hotfix (task #35): bullets container sits inside heroBlock
  // which uses alignItems:'center'. Without alignSelf:'stretch' on the
  // bullets container, the column shrinks to the widest child's
  // intrinsic width — which on device became the circle+gap only,
  // hiding the bullet text. Stretch the container + each Animated.View
  // child so the inner CohortBullet row has horizontal room to lay
  // out its label.
  bullets: {
    gap: spacing.md,
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
    alignSelf: 'stretch',
  },
  // F-S2.W1.hotfix: stretch each animated bullet wrapper to the
  // bullets container width so the inner CohortBullet row's flex:1
  // text has horizontal space to render. Without this, the inner row
  // collapses to 24px (circle width) on device.
  bulletStretch: {
    alignSelf: 'stretch',
  },
  footer: {
    paddingTop: spacing.lg,
  },
});

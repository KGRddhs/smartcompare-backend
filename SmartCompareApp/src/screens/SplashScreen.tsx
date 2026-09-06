import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { colors, typography, spacing } from '../theme';
import QarenLogo from '../components/QarenLogo';

/**
 * A5 — the brand moment is a FLOOR, not a fixed toll.
 *
 * The splash used to hold an unconditional 1.5s from JS mount, and that
 * clock starts AFTER process launch + bundle parse + RN root mount, so it
 * stacked on native startup even when fonts and the auth check were
 * already done (which, since A3's cached-session boot, is the common
 * case). Now it ends as soon as the app is genuinely `ready` AND the
 * short minimum below has passed — capped at the original 1.5s so a slow
 * boot behaves exactly as it did before.
 *
 * MIN keeps the brand moment from flashing (same spirit as the documented
 * 1.2s Home->Results min-display floor); MAX is the unchanged ceiling.
 */
const MIN_SPLASH_MS = 700;
const MAX_SPLASH_MS = 1500;

interface SplashScreenProps {
  onFinish: () => void;
  /**
   * True once fonts are loaded and the initial auth check has settled.
   * Optional on purpose: an omitted `ready` degrades to the legacy
   * hold-until-MAX behaviour, never to something shorter.
   */
  ready?: boolean;
}

export default function SplashScreen({ onFinish, ready = false }: SplashScreenProps) {
  const { t } = useTranslation();
  const logoOpacity = useSharedValue(0);
  const logoScale = useSharedValue(0.8);
  const taglineOpacity = useSharedValue(0);
  const [minElapsed, setMinElapsed] = useState(false);

  // Held in a ref so a changed `onFinish` identity can never re-arm (and
  // thereby restart) the floor timers below.
  const onFinishRef = useRef(onFinish);
  useEffect(() => {
    onFinishRef.current = onFinish;
  }, [onFinish]);

  const finishedRef = useRef(false);
  const finishOnce = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onFinishRef.current();
  }, []);

  useEffect(() => {
    // Logo fades in + scales up
    logoOpacity.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.ease) });
    logoScale.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.ease) });

    // Tagline fades in after 200ms
    taglineOpacity.value = withDelay(200, withTiming(1, { duration: 400 }));
  }, [logoOpacity, logoScale, taglineOpacity]);

  // Deliberately its OWN effect, keyed only on the stable `finishOnce`: the
  // two clocks must be armed EXACTLY once at mount. Sharing the animation
  // effect above would re-arm (and so restart) the floor on any re-render
  // whose shared-value identities moved — which is precisely what the
  // `minElapsed` state update below triggers.
  useEffect(() => {
    // The minimum the brand moment is allowed to be, and the maximum.
    const minTimer = setTimeout(() => setMinElapsed(true), MIN_SPLASH_MS);
    const capTimer = setTimeout(finishOnce, MAX_SPLASH_MS);
    return () => {
      clearTimeout(minTimer);
      clearTimeout(capTimer);
    };
  }, [finishOnce]);

  useEffect(() => {
    // Whichever lands second — readiness or the minimum — releases the splash.
    if (ready && minElapsed) finishOnce();
  }, [ready, minElapsed, finishOnce]);

  const logoStyle = useAnimatedStyle(() => ({
    opacity: logoOpacity.value,
    transform: [{ scale: logoScale.value }],
  }));

  const taglineStyle = useAnimatedStyle(() => ({
    opacity: taglineOpacity.value,
  }));

  return (
    <View style={styles.container}>
      {/* Bundle B/C/D Task 2.10 — glyph + wordmark together. The wordmark
          now reads from i18n so EN testers see "Qaren" not "قارن". */}
      {/* Bundle D Claude-Design (option small, Task 2.F.2 screen 8):
          hero-scale lens glyph (56→128) per SplashScreen.jsx QarenLensGlyph
          — splash is the brand moment, so the logo gets the visual weight.
          Wordmark fontSize 48→40 + tightened letterSpacing matches the
          Claude-Design "Qaren" wordmark proportions (h1 700 40px/1
          letter-spacing: -0.8px). Vertical stack instead of horizontal
          row mirrors the JSX brand-moment composition. */}
      <Animated.View style={[styles.brandStack, logoStyle]}>
        <QarenLogo size={128} />
        <Animated.Text style={styles.logo}>{t('app.name')}</Animated.Text>
      </Animated.View>
      <Animated.Text style={[styles.tagline, taglineStyle]}>
        {t('splash.tagline')}
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.lg,
  },
  // Stacked composition (logo above wordmark) per Claude-Design splash.
  // RTL-safe: alignItems centers in both directions.
  brandStack: {
    alignItems: 'center',
    gap: spacing.base,
  },
  logo: {
    fontSize: 40,
    fontWeight: '700',
    color: colors.text.primary,
    letterSpacing: -0.8,
  },
  tagline: {
    ...typography.body,
    color: colors.text.secondary,
  },
});

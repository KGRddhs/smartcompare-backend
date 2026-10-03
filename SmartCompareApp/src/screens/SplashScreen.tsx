import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, StyleSheet, Dimensions, I18nManager } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { colors, typography, spacing } from '../theme';
import QarenLogo from '../components/QarenLogo';
import { splashMarkLayout } from '../utils/splashMarkLayout';

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
    // Only the tagline animates (D2): it fades in after 200ms. The mark is
    // drawn at full opacity from the first frame (see the render below).
    taglineOpacity.value = withDelay(200, withTiming(1, { duration: 400 }));
  }, [taglineOpacity]);

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

  const taglineStyle = useAnimatedStyle(() => ({
    opacity: taglineOpacity.value,
  }));

  // U4c D2 — the hand-off from the native launch screen. The iOS launch
  // storyboard draws splash-icon.png aspect-fit across the whole window
  // (App.tsx renders this screen bare at the root, so it fills the window
  // too); the JS mark starts on exactly those pixels, at full opacity and
  // not animated, so nothing jumps or fades when the JS splash takes over.
  // D1: the mark stands alone, no app name beside it.
  const { width, height } = Dimensions.get('window');
  const mark = splashMarkLayout({ width, height });
  // React Native swaps left and right under RTL by default (the app forces
  // RTL for Arabic and never calls swapLeftAndRightInRTL(false)), so a
  // physical `left` would land at width - left - size; the launch screen is
  // never mirrored, so pre-mirror it. Read HERE, at render time, never in a
  // module-scope StyleSheet or constant: a module-scope value is frozen at
  // import, before the direction is known.
  const mirrored = I18nManager.isRTL && I18nManager.doLeftAndRightSwapInRTL !== false;
  const markLeft = mirrored ? width - mark.left - mark.size : mark.left;

  return (
    <View style={styles.container}>
      <View
        testID="splash-mark"
        pointerEvents="none"
        style={{
          position: 'absolute',
          left: markLeft,
          top: mark.top,
          width: mark.size,
          height: mark.size,
        }}
      >
        <QarenLogo size={mark.size} />
      </View>
      <Animated.Text
        style={[styles.tagline, { top: mark.top + mark.size + spacing.lg }, taglineStyle]}
      >
        {t('splash.tagline')}
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  // The only animated element (D2). Placed under the mark, centred on the
  // screen; left 0 / right 0 is symmetric, so RTL needs no compensation.
  tagline: {
    position: 'absolute',
    left: 0,
    right: 0,
    textAlign: 'center',
    ...typography.body,
    color: colors.text.secondary,
  },
});

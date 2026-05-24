import React, { useEffect } from 'react';
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

interface SplashScreenProps {
  onFinish: () => void;
}

export default function SplashScreen({ onFinish }: SplashScreenProps) {
  const { t } = useTranslation();
  const logoOpacity = useSharedValue(0);
  const logoScale = useSharedValue(0.8);
  const taglineOpacity = useSharedValue(0);

  useEffect(() => {
    // Logo fades in + scales up
    logoOpacity.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.ease) });
    logoScale.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.ease) });

    // Tagline fades in after 200ms
    taglineOpacity.value = withDelay(200, withTiming(1, { duration: 400 }));

    // After 1.5s total, trigger onFinish
    const timer = setTimeout(onFinish, 1500);
    return () => clearTimeout(timer);
  }, [logoOpacity, logoScale, taglineOpacity, onFinish]);

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

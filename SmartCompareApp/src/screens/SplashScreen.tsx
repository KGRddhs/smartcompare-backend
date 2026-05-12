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
      <Animated.View style={[styles.brandRow, logoStyle]}>
        <QarenLogo size={56} />
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
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  logo: {
    fontSize: 48,
    fontWeight: '700',
    color: colors.text.primary,
  },
  tagline: {
    ...typography.body,
    color: colors.text.secondary,
    marginTop: spacing.sm,
  },
});

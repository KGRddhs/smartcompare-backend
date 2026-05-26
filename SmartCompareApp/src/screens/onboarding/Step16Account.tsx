/**
 * Step16Account — Bundle E S1.3 composition.
 *
 * Re-composed against docs/claude-design-handoff/ui_kits/mobile/AuthScreens.jsx:152-226
 * (QarenSaveAdvisorScreen) per Bundle E plan § Frontend lane S1 + design
 * doc § 3.1 Step16 row.
 *
 * Anatomy:
 *   1. Progress bar at 94% (NO back arrow — forced step)
 *   2. Emerald-tint bookmark-glyph hero (72px circle, accentLight bg,
 *      accentDark bookmark SVG)
 *   3. Headline "Save your advisor." + subtitle
 *   4. SocialRow — Apple (iOS only) / Google / Email triplet
 *   5. OrDivider — hairline + uppercase "OR" + hairline
 *   6. Email AuthField (focus-hint pill — orchestrator routes to real
 *      Register screen when user taps "Save my advisor" or the Email
 *      social pill)
 *   7. Terms & Privacy fine print
 *   8. Sticky black "Save my advisor" CTA (52px, fontWeight 600/16)
 *   9. NO SKIP LINK — per design doc + Apple guideline 4.8 + sunk-cost
 *      drop-off minimum at this step
 *
 * API contract preserved (per __tests__/screens/onboarding/Step16Account.test.tsx):
 *   - onSelectMethod: (method: 'apple' | 'google' | 'email') => void
 *   - appleAvailable?: boolean (defaults to Platform.OS === 'ios')
 *   - testIDs account-apple, account-google, account-email forwarded to
 *     the SocialButton pressables AND the sticky CTA fires
 *     onSelectMethod('email') so the orchestrator routes to email signup
 *
 * Visual primitives (SocialButton + AuthField) are local mirrors of the
 * LoginScreen versions; deduplication into a shared primitive can happen
 * in S3 polish.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import Svg, { Path } from 'react-native-svg';
import { Mail } from 'lucide-react-native';
import { colors, spacing, radii } from '../../theme';

export type AuthMethod = 'apple' | 'google' | 'email';

interface Props {
  onSelectMethod: (method: AuthMethod) => void;
  /** Whether Apple Sign-In is supported on this platform. iOS only. */
  appleAvailable?: boolean;
}

// ---------- Bookmark glyph hero ----------
function BookmarkHero() {
  return (
    <View style={heroStyles.circle} testID="s16-hero">
      <Svg width={32} height={32} viewBox="0 0 24 24">
        <Path
          d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v16l7-3 7 3z"
          fill="none"
          stroke={colors.accentDark}
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    </View>
  );
}

// ---------- SocialButton (mirror of LoginScreen primitive) ----------
interface SocialButtonProps {
  provider: AuthMethod;
  label: string;
  onPress: () => void;
  testID: string;
}

function SocialButton({ provider, label, onPress, testID }: SocialButtonProps) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={socialStyles.btn}
    >
      <SocialGlyph provider={provider} />
      <Text style={socialStyles.label}>{label}</Text>
    </TouchableOpacity>
  );
}

function SocialGlyph({ provider }: { provider: AuthMethod }) {
  if (provider === 'email') {
    return <Mail size={18} color={colors.text.primary} strokeWidth={2} />;
  }
  if (provider === 'apple') {
    return <Text style={socialStyles.glyphApple}></Text>;
  }
  return <Text style={socialStyles.glyphGoogle}>G</Text>;
}

// ---------- Main screen ----------
export function Step16Account({
  onSelectMethod,
  appleAvailable = Platform.OS === 'ios',
}: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [focused, setFocused] = useState(false);

  const onSaveAdvisor = () => {
    // Sticky CTA always routes through the email path — orchestrator
    // (OnboardingFlow) handles the actual email signup. The SocialRow
    // above provides the shortcut paths.
    onSelectMethod('email');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {/* Progress bar — NO back arrow per forced-step rule */}
      <View style={styles.header}>
        <View style={styles.progressTrack}>
          <View style={styles.progressFill} />
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.heroBlock}>
          <BookmarkHero />
        </View>

        <Text style={styles.title}>{t('onboarding.s16.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s16.subtitle')}</Text>

        {/* SocialRow — Apple / Google / Email */}
        <View style={styles.socialRow}>
          {appleAvailable ? (
            <SocialButton
              testID="account-apple"
              provider="apple"
              label={t('onboarding.s16.apple')}
              onPress={() => onSelectMethod('apple')}
            />
          ) : null}
          <SocialButton
            testID="account-google"
            provider="google"
            label={t('onboarding.s16.google')}
            onPress={() => onSelectMethod('google')}
          />
          <SocialButton
            testID="account-email"
            provider="email"
            label={t('onboarding.s16.email')}
            onPress={() => onSelectMethod('email')}
          />
        </View>

        {/* OrDivider */}
        <View style={styles.orRow}>
          <View style={styles.orLine} />
          <Text style={styles.orText}>
            {t('auth.or', { defaultValue: 'OR' })}
          </Text>
          <View style={styles.orLine} />
        </View>

        {/* Email AuthField (focus hint) */}
        <View style={fieldStyles.wrap}>
          <Text style={fieldStyles.label}>{t('auth.email', { defaultValue: 'Email' })}</Text>
          <View
            style={[
              fieldStyles.box,
              focused ? fieldStyles.boxFocused : fieldStyles.boxRest,
            ]}
          >
            <TextInput
              testID="account-email-input"
              value={email}
              onChangeText={setEmail}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder={t('auth.emailPlaceholder', {
                defaultValue: 'you@example.com',
              })}
              placeholderTextColor={colors.text.placeholder}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              textContentType="emailAddress"
              style={fieldStyles.input}
            />
          </View>
        </View>

        {/* Terms & Privacy fine print */}
        <Text style={styles.terms}>
          {t('onboarding.s16.termsPrefix', {
            defaultValue: 'By continuing, you agree to our ',
          })}
          <Text style={styles.termsLink}>
            {t('common.terms', { defaultValue: 'Terms' })}
          </Text>
          <Text> &amp; </Text>
          <Text style={styles.termsLink}>
            {t('common.privacy', { defaultValue: 'Privacy Policy' })}
          </Text>
          .
        </Text>
      </ScrollView>

      {/* Sticky bottom CTA — NO skip link */}
      <View style={styles.footer}>
        <TouchableOpacity
          testID="account-save-advisor"
          onPress={onSaveAdvisor}
          activeOpacity={0.85}
          accessibilityRole="button"
          accessibilityLabel={t('onboarding.s16.save', {
            defaultValue: 'Save my advisor',
          })}
          style={styles.ctaBtn}
        >
          <Text style={styles.ctaText}>
            {t('onboarding.s16.save', { defaultValue: 'Save my advisor' })}
          </Text>
        </TouchableOpacity>
        {/* NO skip link — forced per design system rule + Apple guideline 4.8. */}
      </View>
    </KeyboardAvoidingView>
  );
}

// ---------- Styles ----------
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
    paddingTop: 50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.base,
  },
  progressTrack: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border.light,
    overflow: 'hidden',
  },
  progressFill: {
    width: '94%',
    height: '100%',
    backgroundColor: colors.cta.primary,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing.xl,
    paddingBottom: spacing.lg,
  },
  heroBlock: {
    alignItems: 'center',
    marginBottom: 18,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    lineHeight: 28 * 1.2,
    letterSpacing: -0.32,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  subtitle: {
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 14 * 1.5,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 320,
    alignSelf: 'center',
    marginBottom: spacing.xl,
  },
  socialRow: {
    flexDirection: 'row',
    gap: 8,
  },
  orRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginVertical: 20,
  },
  orLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.border.light,
  },
  orText: {
    fontSize: 11,
    fontWeight: '500',
    lineHeight: 11 * 1.3,
    color: colors.text.placeholder,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  terms: {
    fontSize: 11,
    fontWeight: '400',
    lineHeight: 11 * 1.5,
    color: colors.text.placeholder,
    textAlign: 'center',
    marginTop: 18,
  },
  termsLink: {
    color: colors.text.secondary,
    textDecorationLine: 'underline',
  },
  footer: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.base,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
    backgroundColor: colors.bg.primary,
  },
  ctaBtn: {
    width: '100%',
    height: 52,
    borderRadius: radii.chip,
    backgroundColor: colors.cta.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 16 * 1.5,
    color: colors.cta.onPrimary,
  },
});

const heroStyles = StyleSheet.create({
  circle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

const socialStyles = StyleSheet.create({
  btn: {
    flex: 1,
    minHeight: 48,
    borderRadius: 12,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.medium,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingHorizontal: spacing.sm,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 13,
    color: colors.text.primary,
  },
  glyphApple: {
    fontSize: 18,
    lineHeight: 18,
    color: colors.text.primary,
    fontWeight: '700',
  },
  glyphGoogle: {
    fontSize: 16,
    lineHeight: 16,
    color: '#4285F4',
    fontWeight: '700',
  },
});

const fieldStyles = StyleSheet.create({
  wrap: {
    gap: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
  },
  box: {
    height: 48,
    paddingHorizontal: 14,
    borderRadius: 12,
    backgroundColor: colors.bg.primary,
    flexDirection: 'row',
    alignItems: 'center',
  },
  boxRest: {
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  boxFocused: {
    borderWidth: 2,
    borderColor: colors.text.primary,
  },
  input: {
    flex: 1,
    fontSize: 16,
    fontWeight: '400',
    lineHeight: 16 * 1.5,
    color: colors.text.primary,
    padding: 0,
  },
});

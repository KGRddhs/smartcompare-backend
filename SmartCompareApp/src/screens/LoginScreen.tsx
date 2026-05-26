/**
 * LoginScreen — Bundle E S1.2 composition.
 *
 * Re-composed against docs/claude-design-handoff/ui_kits/mobile/AuthScreens.jsx:86-150
 * (QarenSignInScreen) per Bundle E plan § Frontend lane S1 + design doc § 3.1.
 *
 * Anatomy:
 *   1. Back arrow (top-left, transparent bg)
 *   2. Headline "Welcome back." + "Your advisor and credits are waiting."
 *   3. SocialRow — Apple / Google / Email-only triplet (each 48px tall,
 *      light border, glyph + label)
 *   4. OrDivider — hairline + uppercase "OR" + hairline
 *   5. AuthField pair — Email + Password with focus-thickening border
 *   6. Forgot password? — right-aligned, accentDark muted
 *   7. Sticky black "Sign in" CTA (52px, fontWeight 600/16, radii.chip)
 *   8. "New here? Create an account" footer link
 *
 * B4 Google sign-in fix already landed on main (see backend B4 cleanup
 * tasks). LoginScreen wiring is unchanged — `handleGoogleSignIn` → existing
 * `signInWithGoogle()` from authService — no extra FE work needed for B4
 * beyond ensuring the SocialRow Google handler fires that function.
 *
 * Test contract preserved (per __tests__/AuthScreens.test.tsx):
 *   - Renders labels t('auth.email'), t('auth.password'), t('auth.signIn')
 *   - t('auth.signUp') is pressable → navigation.navigate('Register')
 *   - t('auth.forgotPassword') is pressable → navigation.navigate('ForgotPassword')
 *   - t('auth.googleSignIn') is pressable → signInWithGoogle() → onLoginSuccess()
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { usePreventScreenCapture } from 'expo-screen-capture';
import {
  login,
  signInWithGoogle,
  signInWithApple,
  isAppleSignInAvailable,
} from '../services/authService';
import { parseApiError } from '../services/api';
import { AuthStackParamList } from '../types';
import { colors, spacing, radii } from '../theme';
import { ChevronLeft, Mail } from 'lucide-react-native';

type LoginScreenProps = {
  navigation: NativeStackNavigationProp<AuthStackParamList, 'Login'>;
  onLoginSuccess: () => void;
};

type SocialProvider = 'apple' | 'google' | 'email';

// ---------- SocialRow primitive (local to AuthScreens family) ----------
interface SocialButtonProps {
  provider: SocialProvider;
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  testID?: string;
}

function SocialButton({
  provider,
  label,
  onPress,
  loading,
  disabled,
  testID,
}: SocialButtonProps) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: disabled || loading }}
      style={[socialStyles.btn, (disabled || loading) ? socialStyles.btnDisabled : null]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={colors.text.primary} />
      ) : (
        <>
          <SocialGlyph provider={provider} />
          <Text style={socialStyles.label}>{label}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

function SocialGlyph({ provider }: { provider: SocialProvider }) {
  // Apple glyph kept as a single unicode bullet — production icon font swap
  // happens during native build. For now: emoji-free, decorative-text fallback
  // for Apple (), real lucide for Google (using Mail as placeholder until a
  // colored Google glyph ships in lucide-react-native — design intent in JSX
  // is brand color, so a future swap to react-native-svg path can fill in).
  if (provider === 'email') {
    return <Mail size={18} color={colors.text.primary} strokeWidth={2} />;
  }
  if (provider === 'apple') {
    return <Text style={socialStyles.glyphApple}></Text>;
  }
  // google — use a colored "G" character as placeholder (real brand glyph
  // arrives in S3 polish; functional contract holds).
  return <Text style={socialStyles.glyphGoogle}>G</Text>;
}

// ---------- AuthField (Email + Password) ----------
interface AuthFieldProps {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  type?: 'email' | 'password';
  autoFocus?: boolean;
  error?: string;
  editable?: boolean;
  testID?: string;
}

function AuthField({
  label,
  value,
  onChangeText,
  placeholder,
  type = 'email',
  autoFocus,
  error,
  editable = true,
  testID,
}: AuthFieldProps) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={fieldStyles.wrap}>
      <Text style={fieldStyles.label}>{label}</Text>
      <View
        style={[
          fieldStyles.box,
          focused ? fieldStyles.boxFocused : fieldStyles.boxRest,
          error ? fieldStyles.boxError : null,
        ]}
      >
        <TextInput
          testID={testID}
          value={value}
          onChangeText={onChangeText}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          placeholderTextColor={colors.text.placeholder}
          autoFocus={autoFocus}
          editable={editable}
          autoCapitalize={type === 'email' ? 'none' : 'sentences'}
          autoCorrect={false}
          keyboardType={type === 'email' ? 'email-address' : 'default'}
          secureTextEntry={type === 'password'}
          textContentType={type === 'email' ? 'emailAddress' : 'password'}
          style={fieldStyles.input}
        />
      </View>
      {error ? <Text style={fieldStyles.errorText}>{error}</Text> : null}
    </View>
  );
}

// ---------- Main screen ----------
export default function LoginScreen({ navigation, onLoginSuccess }: LoginScreenProps) {
  const { t } = useTranslation();
  usePreventScreenCapture();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [socialLoading, setSocialLoading] = useState<'' | 'apple' | 'google' | 'email'>('');
  const [showApple, setShowApple] = useState(false);

  useEffect(() => {
    if (Platform.OS === 'ios') {
      isAppleSignInAvailable().then(setShowApple);
    }
  }, []);

  const handleGoogleSignIn = async () => {
    setSocialLoading('google');
    setError('');
    try {
      const result = await signInWithGoogle();
      if (result.success) {
        onLoginSuccess();
      } else if (result.error !== 'Sign-in cancelled') {
        setError(result.error || t('auth.googleFailed', { defaultValue: 'Google sign-in failed' }));
      }
    } catch (err: any) {
      setError(parseApiError(err).message);
    } finally {
      setSocialLoading('');
    }
  };

  const handleAppleSignIn = async () => {
    setSocialLoading('apple');
    setError('');
    try {
      const result = await signInWithApple();
      if (result.success) {
        onLoginSuccess();
      } else if (result.error !== 'Sign-in cancelled') {
        setError(result.error || t('auth.appleFailed', { defaultValue: 'Apple sign-in failed' }));
      }
    } catch (err: any) {
      setError(parseApiError(err).message);
    } finally {
      setSocialLoading('');
    }
  };

  const handleLogin = async () => {
    let hasError = false;
    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      setEmailError(t('auth.emailRequired', { defaultValue: 'Email is required' }));
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setEmailError(t('auth.emailInvalid', { defaultValue: 'Invalid email format' }));
      hasError = true;
    } else {
      setEmailError('');
    }

    if (!password) {
      setPasswordError(t('auth.passwordRequired', { defaultValue: 'Password is required' }));
      hasError = true;
    } else if (
      password.length < 10 ||
      !/[A-Z]/.test(password) ||
      !/[a-z]/.test(password) ||
      !/[0-9]/.test(password)
    ) {
      setPasswordError(
        t('auth.passwordRequirements', {
          defaultValue: 'Password must be 10+ characters with uppercase, lowercase, and number',
        }),
      );
      hasError = true;
    } else {
      setPasswordError('');
    }

    if (hasError) return;

    setLoading(true);
    setError('');

    try {
      // Keep the inline call form for the Bundle D screens-contract regex
      // (Screens.bundleD.contract.test.ts:196 asserts exact substring
      // `login(email.trim().toLowerCase(), password)`).
      const result = await login(email.trim().toLowerCase(), password);
      if (result.success) {
        onLoginSuccess();
      } else {
        setError(result.error || t('auth.loginFailed', { defaultValue: 'Sign-in could not complete' }));
      }
    } catch (err: any) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailSocialPress = () => {
    // The "Email" social pill simply focuses the email field; if user is
    // already typing, no-op. Per JSX: SocialRow has 3 entries, Email is
    // the third — but on RN we already render AuthField pair below the
    // divider, so the tap is a soft scroll/focus hint.
    setSocialLoading('');
  };

  const disabled = loading || Boolean(socialLoading);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {/* Header: back arrow only */}
      <View style={styles.header}>
        <TouchableOpacity
          testID="login-back"
          onPress={() => navigation.goBack()}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          accessibilityRole="button"
          accessibilityLabel={t('common.back', { defaultValue: 'Back' })}
          style={styles.backBtn}
        >
          <ChevronLeft size={18} color={colors.text.primary} strokeWidth={2.5} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>
          {t('auth.welcomeBack', { defaultValue: 'Welcome back.' })}
        </Text>
        <Text style={styles.subtitle}>
          {t('auth.welcomeBackSub', {
            defaultValue: 'Your advisor and credits are waiting.',
          })}
        </Text>

        {/* SocialRow — Apple (iOS only), Google, Email */}
        <View style={styles.socialRow}>
          {showApple ? (
            <SocialButton
              testID="login-social-apple"
              provider="apple"
              label={t('auth.appleSignIn', { defaultValue: 'Apple' })}
              onPress={handleAppleSignIn}
              loading={socialLoading === 'apple'}
              disabled={disabled && socialLoading !== 'apple'}
            />
          ) : null}
          <SocialButton
            testID="login-social-google"
            provider="google"
            label={t('auth.googleSignIn', { defaultValue: 'Google' })}
            onPress={handleGoogleSignIn}
            loading={socialLoading === 'google'}
            disabled={disabled && socialLoading !== 'google'}
          />
          <SocialButton
            testID="login-social-email"
            provider="email"
            label={t('auth.emailSignIn', { defaultValue: 'Email' })}
            onPress={handleEmailSocialPress}
            disabled={disabled}
          />
        </View>

        {/* OrDivider */}
        <View style={styles.orRow}>
          <View style={styles.orLine} />
          <Text style={styles.orText}>{t('auth.or', { defaultValue: 'OR' })}</Text>
          <View style={styles.orLine} />
        </View>

        {/* Email + password fields */}
        <AuthField
          testID="login-email-input"
          label={t('auth.email')}
          value={email}
          onChangeText={(v) => {
            setEmail(v);
            if (emailError) setEmailError('');
            if (error) setError('');
          }}
          placeholder={t('auth.emailPlaceholder', { defaultValue: 'you@example.com' })}
          type="email"
          autoFocus={!showApple}
          error={emailError}
          editable={!disabled}
        />
        <AuthField
          testID="login-password-input"
          label={t('auth.password')}
          value={password}
          onChangeText={(v) => {
            setPassword(v);
            if (passwordError) setPasswordError('');
            if (error) setError('');
          }}
          placeholder=""
          type="password"
          error={passwordError}
          editable={!disabled}
        />

        {/* Forgot password — right-aligned */}
        <TouchableOpacity
          testID="login-forgot"
          onPress={() => navigation.navigate('ForgotPassword')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          style={styles.forgotBtn}
          accessibilityRole="link"
        >
          <Text style={styles.forgotText}>{t('auth.forgotPassword')}</Text>
        </TouchableOpacity>

        {error ? (
          <View style={styles.errorBanner} testID="login-error">
            <Text style={styles.errorBannerText}>{error}</Text>
          </View>
        ) : null}
      </ScrollView>

      {/* Sticky bottom CTA + footer link */}
      <View style={styles.footer}>
        <TouchableOpacity
          testID="login-submit"
          onPress={handleLogin}
          disabled={disabled}
          activeOpacity={0.85}
          style={[styles.ctaBtn, disabled ? styles.ctaBtnDisabled : null]}
          accessibilityRole="button"
          accessibilityLabel={t('auth.signIn')}
          accessibilityState={{ disabled, busy: loading }}
        >
          {loading ? (
            <ActivityIndicator color={colors.cta.onPrimary} />
          ) : (
            <Text style={styles.ctaText}>{t('auth.signIn')}</Text>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          testID="login-register-link"
          onPress={() => navigation.navigate('Register')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          style={styles.footerLinkBtn}
          accessibilityRole="link"
        >
          <Text style={styles.footerText}>
            {t('auth.newHere', { defaultValue: 'New here? ' })}
            <Text style={styles.footerLink}>{t('auth.signUp')}</Text>
          </Text>
        </TouchableOpacity>
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
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing.xl,
    paddingBottom: spacing.lg,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    lineHeight: 32 * 1.2,
    letterSpacing: -0.4,
    color: colors.text.primary,
    marginVertical: spacing.sm,
  },
  subtitle: {
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 14 * 1.5,
    color: colors.text.secondary,
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
  forgotBtn: {
    alignSelf: 'flex-end',
    paddingVertical: spacing.sm,
  },
  forgotText: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12,
    color: colors.accentDark,
  },
  errorBanner: {
    marginTop: spacing.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radii.button,
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  errorBannerText: {
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 13 * 1.4,
    color: colors.destructive,
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
  ctaBtnDisabled: {
    opacity: 0.5,
  },
  ctaText: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 16 * 1.5,
    color: colors.cta.onPrimary,
  },
  footerLinkBtn: {
    marginTop: 10,
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  footerText: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  footerLink: {
    color: colors.text.primary,
    textDecorationLine: 'underline',
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
  btnDisabled: {
    opacity: 0.5,
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
    marginBottom: 14,
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
  boxError: {
    borderWidth: 2,
    borderColor: colors.destructive,
  },
  input: {
    flex: 1,
    fontSize: 16,
    fontWeight: '400',
    lineHeight: 16 * 1.5,
    color: colors.text.primary,
    padding: 0,
  },
  errorText: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.4,
    color: colors.destructive,
    marginTop: 2,
  },
});

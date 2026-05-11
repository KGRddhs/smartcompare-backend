/**
 * Qaren - Register Screen
 * Restyled with theme tokens + i18n. All auth logic preserved.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { usePreventScreenCapture } from 'expo-screen-capture';
import { register, signInWithGoogle, signInWithApple, isAppleSignInAvailable } from '../services/authService';
import { parseApiError } from '../services/api';
import { AuthStackParamList } from '../types';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { Button } from '../components/Button';

type RegisterScreenProps = NativeStackScreenProps<AuthStackParamList, 'Register'> & {
  onRegisterSuccess: () => void;
};

export default function RegisterScreen({ navigation, route, onRegisterSuccess }: RegisterScreenProps) {
  const { t } = useTranslation();
  usePreventScreenCapture();
  // F3.5 — invite_id is forwarded from the InviteeQuiz soft-signup CTA so
  // the backend links the new user to the pending referral invite. When
  // the user reaches Register from the auth tab directly, this is undefined.
  const inviteId = route?.params?.invite_id;
  const inviteCodeFromDeepLink = route?.params?.code;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [inviteCode, setInviteCode] = useState<string>(inviteCodeFromDeepLink ?? '');
  const [inviteCodeLocked, setInviteCodeLocked] = useState<boolean>(!!inviteCodeFromDeepLink);
  const [inviteCodeError, setInviteCodeError] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmError, setConfirmError] = useState('');
  const [socialLoading, setSocialLoading] = useState('');
  const [showApple, setShowApple] = useState(false);

  // Format: QR- followed by 6 chars from an unambiguous alphabet (no I/O/1/0).
  // Server is authoritative on validity; client just guards the obvious shape.
  const inviteCodeRegex = /^QR-[A-HJ-NP-Z2-9]{6}$/;

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
        onRegisterSuccess();
      } else if (result.error !== 'Sign-in cancelled') {
        setError(result.error || 'Google sign-in failed');
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
        onRegisterSuccess();
      } else if (result.error !== 'Sign-in cancelled') {
        setError(result.error || 'Apple sign-in failed');
      }
    } catch (err: any) {
      setError(parseApiError(err).message);
    } finally {
      setSocialLoading('');
    }
  };

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleRegister = async () => {
    let hasError = false;
    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      setEmailError(t('auth.email') + ' is required');
      hasError = true;
    } else if (!validateEmail(trimmedEmail)) {
      setEmailError('Invalid email format');
      hasError = true;
    } else {
      setEmailError('');
    }

    if (!password) {
      setPasswordError(t('auth.password') + ' is required');
      hasError = true;
    } else if (password.length < 10 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password)) {
      setPasswordError('Password must be at least 10 characters with 1 uppercase, 1 lowercase, and 1 digit');
      hasError = true;
    } else {
      setPasswordError('');
    }

    if (!confirmPassword) {
      setConfirmError('Please confirm your password');
      hasError = true;
    } else if (password !== confirmPassword) {
      setConfirmError('Passwords do not match');
      hasError = true;
    } else {
      setConfirmError('');
    }

    if (inviteCode && !inviteCodeRegex.test(inviteCode)) {
      setInviteCodeError(t('register.inviteCode.invalid'));
      hasError = true;
    } else {
      setInviteCodeError('');
    }

    if (hasError) return;

    setLoading(true);
    setError('');

    try {
      const result = await register(email.trim().toLowerCase(), password, {
        inviteId,
        inviteCode: inviteCode || undefined,
      });

      if (result.success) {
        onRegisterSuccess();
      } else {
        setError(result.error || 'Registration failed');
      }
    } catch (err: any) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.content}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.logo}>قارن</Text>
              <Text style={styles.subtitle}>{t('splash.tagline')}</Text>
            </View>

            {/* Register Form */}
            <View style={styles.form}>
              <Text style={styles.title}>{t('auth.signUp')}</Text>

              {error ? (
                <View style={styles.errorContainer}>
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              ) : null}

              <View style={styles.inputContainer}>
                <Text style={styles.label}>{t('auth.email')}</Text>
                <TextInput
                  style={[styles.input, emailError ? styles.inputError : null]}
                  placeholder={t('auth.email')}
                  placeholderTextColor={colors.text.placeholder}
                  value={email}
                  onChangeText={(text) => { setEmail(text); setEmailError(''); }}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  editable={!loading}
                />
                {emailError ? <Text style={styles.fieldError}>{emailError}</Text> : null}
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>{t('auth.password')}</Text>
                <TextInput
                  style={[styles.input, passwordError ? styles.inputError : null]}
                  placeholder={t('auth.password')}
                  placeholderTextColor={colors.text.placeholder}
                  value={password}
                  onChangeText={(text) => { setPassword(text); setPasswordError(''); }}
                  secureTextEntry
                  editable={!loading}
                />
                {passwordError ? <Text style={styles.fieldError}>{passwordError}</Text> : null}
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>{t('auth.confirmPassword')}</Text>
                <TextInput
                  style={[styles.input, confirmError ? styles.inputError : null]}
                  placeholder={t('auth.confirmPassword')}
                  placeholderTextColor={colors.text.placeholder}
                  value={confirmPassword}
                  onChangeText={(text) => { setConfirmPassword(text); setConfirmError(''); }}
                  secureTextEntry
                  editable={!loading}
                />
                {confirmError ? <Text style={styles.fieldError}>{confirmError}</Text> : null}
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>{t('register.inviteCode.label')}</Text>
                <View style={styles.inviteCodeRow}>
                  <TextInput
                    style={[
                      styles.input,
                      styles.inviteCodeInput,
                      inviteCodeError ? styles.inputError : null,
                    ]}
                    placeholder={t('register.inviteCode.placeholder')}
                    placeholderTextColor={colors.text.placeholder}
                    value={inviteCode}
                    onChangeText={(v) => {
                      setInviteCode(v.toUpperCase().replace(/[^A-Z0-9-]/g, ''));
                      setInviteCodeError('');
                    }}
                    editable={!loading && !inviteCodeLocked}
                    autoCapitalize="characters"
                    autoCorrect={false}
                    maxLength={9}
                    accessibilityLabel={t('register.inviteCode.accessibility')}
                  />
                  {inviteCodeLocked ? (
                    <TouchableOpacity
                      onPress={() => {
                        setInviteCode('');
                        setInviteCodeLocked(false);
                        setInviteCodeError('');
                      }}
                      style={styles.inviteCodeClear}
                      accessibilityLabel={t('register.inviteCode.clear')}
                    >
                      <Text style={styles.inviteCodeClearText}>×</Text>
                    </TouchableOpacity>
                  ) : null}
                </View>
                {inviteCodeError ? <Text style={styles.fieldError}>{inviteCodeError}</Text> : null}
              </View>

              <Button
                title={t('auth.register')}
                onPress={handleRegister}
                disabled={loading}
                loading={loading}
              />

              {/* Social Sign-In */}
              <View style={styles.dividerRow}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>{t('common.or')}</Text>
                <View style={styles.dividerLine} />
              </View>

              <Button
                title={t('auth.googleSignIn')}
                variant="secondary"
                onPress={handleGoogleSignIn}
                disabled={!!socialLoading || loading}
                loading={socialLoading === 'google'}
              />

              {showApple && (
                <View style={styles.socialSpacer}>
                  <TouchableOpacity
                    style={styles.appleButton}
                    onPress={handleAppleSignIn}
                    disabled={!!socialLoading || loading}
                  >
                    {socialLoading === 'apple' ? (
                      <ActivityIndicator size="small" color="#FFF" />
                    ) : (
                      <Text style={styles.appleButtonText}>{t('auth.appleSignIn')}</Text>
                    )}
                  </TouchableOpacity>
                </View>
              )}

              {/* Benefits */}
              <View style={styles.benefits}>
                <Text style={styles.benefitsTitle}>Free Account Includes:</Text>
                <Text style={styles.benefitItem}>✓ 5 comparisons per day</Text>
                <Text style={styles.benefitItem}>✓ AI-powered product identification</Text>
                <Text style={styles.benefitItem}>✓ Live price comparison</Text>
                <Text style={styles.benefitItem}>✓ Comparison history</Text>
              </View>
            </View>

            {/* Login Link */}
            <View style={styles.footer}>
              <Text style={styles.footerText}>{t('auth.hasAccount')}</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                <Text style={styles.loginLink}>{t('auth.signIn')}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.secondary,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    padding: spacing.xl,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing['2xl'],
  },
  logo: {
    fontSize: 36,
    fontWeight: '700',
    color: colors.text.primary,
  },
  subtitle: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: spacing.sm,
  },
  form: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    padding: spacing.xl,
    ...shadows.card,
  },
  title: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: spacing.xl,
    textAlign: 'center',
  },
  errorContainer: {
    backgroundColor: '#FEF2F2',
    borderRadius: spacing.sm,
    padding: spacing.md,
    marginBottom: spacing.base,
  },
  errorText: {
    ...typography.caption,
    color: colors.destructive,
    textAlign: 'center',
  },
  inputContainer: {
    marginBottom: spacing.base,
  },
  label: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  input: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.input,
    padding: spacing.md,
    ...typography.body,
    color: colors.text.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  inputError: {
    borderColor: colors.destructive,
  },
  inviteCodeRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  inviteCodeInput: {
    flex: 1,
    letterSpacing: 1,
  },
  inviteCodeClear: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginStart: spacing.sm,
    backgroundColor: colors.bg.secondary,
  },
  inviteCodeClearText: {
    fontSize: 18,
    color: colors.text.secondary,
    lineHeight: 20,
  },
  fieldError: {
    ...typography.small,
    color: colors.destructive,
    marginTop: spacing.xs,
  },
  benefits: {
    marginTop: spacing.lg,
    paddingTop: spacing.base,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
  },
  benefitsTitle: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  benefitItem: {
    ...typography.small,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: spacing.xl,
  },
  footerText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  loginLink: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
    marginStart: spacing.xs,
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: spacing.base,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.border.light,
  },
  dividerText: {
    marginHorizontal: spacing.md,
    ...typography.caption,
    color: colors.text.placeholder,
  },
  socialSpacer: {
    marginTop: spacing.sm,
  },
  appleButton: {
    backgroundColor: '#000',
    borderRadius: radii.button,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  appleButtonText: {
    ...typography.body,
    fontWeight: '600',
    color: '#FFF',
  },
});

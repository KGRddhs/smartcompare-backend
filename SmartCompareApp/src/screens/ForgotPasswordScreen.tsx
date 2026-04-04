/**
 * Qaren - Forgot Password Screen
 * Restyled with theme tokens + i18n. All auth logic preserved.
 */

import React, { useState } from 'react';
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
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { usePreventScreenCapture } from 'expo-screen-capture';
import { requestPasswordReset } from '../services/authService';
import { parseApiError } from '../services/api';
import { AuthStackParamList } from '../types';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { Button } from '../components/Button';

type ForgotPasswordScreenProps = {
  navigation: NativeStackNavigationProp<AuthStackParamList, 'ForgotPassword'>;
};

export default function ForgotPasswordScreen({ navigation }: ForgotPasswordScreenProps) {
  const { t } = useTranslation();
  usePreventScreenCapture();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleReset = async () => {
    if (!email.trim()) {
      setError(t('auth.email') + ' is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await requestPasswordReset(email.trim().toLowerCase());
      setSent(true);
    } catch (err: any) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          <View style={styles.successContainer}>
            <Text style={styles.successEmoji}>📧</Text>
            <Text style={styles.successTitle}>{t('auth.resetSent')}</Text>
            <Text style={styles.successText}>
              If an account exists for {email}, you will receive a password reset link shortly.
            </Text>
            <Button
              title={t('auth.signIn')}
              onPress={() => navigation.navigate('Login')}
            />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.logo}>قارن</Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <Text style={styles.title}>{t('auth.resetPassword')}</Text>
            <Text style={styles.description}>
              {t('auth.resetInstructions')}
            </Text>

            {error ? (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <View style={styles.inputContainer}>
              <Text style={styles.label}>{t('auth.email')}</Text>
              <TextInput
                style={styles.input}
                placeholder={t('auth.email')}
                placeholderTextColor={colors.text.placeholder}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                editable={!loading}
              />
            </View>

            <Button
              title={t('auth.resetPassword')}
              onPress={handleReset}
              disabled={loading}
              loading={loading}
            />
          </View>

          {/* Back Link */}
          <TouchableOpacity
            style={styles.backLink}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.backLinkText}>← {t('auth.signIn')}</Text>
          </TouchableOpacity>
        </View>
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
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  description: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: spacing.xl,
    lineHeight: typography.caption.lineHeight * 1.3,
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
    marginBottom: spacing.lg,
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
  backLink: {
    marginTop: spacing.xl,
    alignItems: 'center',
  },
  backLinkText: {
    ...typography.caption,
    color: colors.accent,
  },
  successContainer: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    padding: spacing['2xl'],
    alignItems: 'center',
    ...shadows.card,
  },
  successEmoji: {
    fontSize: 48,
    marginBottom: spacing.base,
  },
  successTitle: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  successText: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: typography.caption.lineHeight * 1.3,
    marginBottom: spacing.xl,
  },
});
